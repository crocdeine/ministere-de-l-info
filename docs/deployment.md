# Déploiement et exploitation

Deux modes d'exécution coexistent :

| Mode | Rôle | Référence |
|---|---|---|
| **Natif** (uv + LaunchAgent macOS) | **Mode principal** sur le Mac mini de Mathias | [ADR-0012](adr/0012-execution-native-mac.md), §1 à §3 |
| **Docker / OrbStack** | **Repli** pendant la transition (2 semaines), puis distribution éventuelle à des tiers (`deploy/install.sh`) | §4 |

La publication des releases (image + base) est décrite dans
[`deploy/README-deploy.md`](../deploy/README-deploy.md).

Convention de ce document : les blocs de commandes se copient-collent tels quels dans
le Terminal. Ils ne contiennent volontairement aucun commentaire `#` : le Terminal de
macOS utilise zsh, qui par défaut transmet un `# commentaire` comme argument de la
commande au lieu de l'ignorer. Le dossier du projet est supposé être `~/Documents/Docker/ministere-de-l-info` ;
s'il est ailleurs, remplacer ce chemin dans la première commande `cd` de chaque bloc.

---

## 1. Mode natif — principe

```
┌──────────────────────────── Mac mini (macOS, Apple Silicon) ───────────────────────────┐
│                                                                                         │
│  LaunchAgent com.crocdeine.ministere-info.native  (démarre à l'ouverture de session,    │
│        │                                           relance en cas de plantage)          │
│        ▼                                                                                │
│  <projet>/.venv/bin/python -m streamlit run app.py  ── écoute 127.0.0.1:<port> ──►  navigateur
│        │  lit (lecture seule)                                                           │
│        ▼                                                                                │
│  MINISTERE_DB_PATH = <projet>/data/ministere.duckdb   ◄── écrit par l'ETL (app arrêtée) │
│        │  copie cohérente chaque jour à 3 h                                             │
│        ▼                                                                                │
│  LaunchAgent com.crocdeine.ministere-info.backup ──► BACKUP_DEST (disque externe, iCloud…)
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

- L'application tourne **depuis le dossier du projet** (le même que pour le développement
  et l'ETL). Justification : un seul utilisateur, un seul exemplaire du code et de la base,
  pas de copie à synchroniser (voir ADR-0012). Conséquence : une modification du code
  n'est prise en compte qu'au redémarrage (`start.sh`) — le rechargement automatique est
  désactivé pour l'app de tous les jours.
- L'app n'écoute que sur `127.0.0.1` : elle n'est pas visible depuis le réseau local.
- Aucune connexion Internet n'est nécessaire au démarrage (pas de `uv run`, extension
  spatial préinstallée).

### Fichiers et emplacements

| Élément | Emplacement |
|---|---|
| Scripts | `<projet>/deploy/native/` : `install-native.sh`, `start.sh`, `stop.sh`, `status.sh`, `uninstall-native.sh` |
| Configuration enregistrée | `~/.config/ministere-info/native.conf` (projet, base, port, sauvegarde) |
| LaunchAgent application | `~/Library/LaunchAgents/com.crocdeine.ministere-info.native.plist` (généré depuis `deploy/native/ministere-info.plist`) |
| LaunchAgent sauvegarde | `~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist` (généré depuis `scripts/com.crocdeine.ministere-info.backup.plist`) |
| Journaux | `~/Library/Logs/ministere-info/` : `app.err.log`, `app.out.log`, `backup.log` (visibles dans l'app Console) |
| Base | `MINISTERE_DB_PATH`, défaut `<projet>/data/ministere.duckdb` |
| Sauvegardes | `BACKUP_DEST`, défaut `<projet>/data/backups/` (à remplacer par un disque externe, voir §2.5) |

### Variables

| Variable | Défaut | Utilisée par |
|---|---|---|
| `MINISTERE_DB_PATH` | `<projet>/data/ministere.duckdb` | application (`src/ministere_de_l_info/config.py`), sauvegarde |
| `MINISTERE_PORT` | `8502`, puis `8501` après la bascule | `install-native.sh` |
| `BACKUP_DEST` | `<projet>/data/backups` | sauvegarde |
| `BACKUP_RETENTION_DAYS` | `7` | sauvegarde |
| `MINISTERE_NATIVE_CONF` | `~/.config/ministere-info/native.conf` | tous les scripts |

Priorité : option de `install-native.sh` > variable d'environnement > `native.conf` > défaut.
Les valeurs retenues sont enregistrées dans `native.conf` et réutilisées aux relances.

`MINISTERE_DB_PATH` n'est lue par l'application qu'à partir de l'intégration de
`src/ministere_de_l_info/config.py` ; avant, l'application lit toujours
`<projet>/data/ministere.duckdb`, qui est aussi la valeur par défaut. Ne pas utiliser
`install-native.sh --base` avant cette intégration.

---

## 2. Mode natif — opérations courantes

### 2.1 Savoir si tout va bien

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/status.sh
```

Vérification : la ligne `Santé` indique `OK (répond)` ; la section « Sauvegardes » donne la date de la dernière
sauvegarde. L'app est à l'adresse indiquée (`http://localhost:8501` après la bascule).

### 2.2 Arrêter, démarrer, redémarrer

Arrêter (jusqu'au prochain `start.sh` ou à la prochaine ouverture de session) :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/stop.sh
```

Démarrer, ou redémarrer si l'app tourne déjà :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/start.sh
```

### 2.3 Mettre à jour le code

```bash
cd ~/Documents/Docker/ministere-de-l-info
git pull
./deploy/native/install-native.sh
```

`install-native.sh` est idempotent : il resynchronise les dépendances (`uv sync --frozen`),
réinstalle l'extension spatial si la version de DuckDB a changé, puis redémarre l'app avec
les paramètres enregistrés.

### 2.4 Lancer un ETL (écriture dans la base)

DuckDB n'accepte aucun écrivain tant qu'un programme lit la base. Il faut donc arrêter
l'app (et, pendant la période de double fonctionnement, le conteneur Docker s'il lit le
même fichier). Exemple avec `load_economie.py`, à remplacer par le script ETL voulu :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/stop.sh
uv run python scripts/load_economie.py
./deploy/native/start.sh
```

Si l'ETL affiche `Could not set lock on file`, un programme lit encore la base : vérifier
`./deploy/native/status.sh` (et `docker ps` pendant la transition). Une sauvegarde lancée
pendant un ETL s'abandonne d'elle-même (code 4) sans rien abîmer.

### 2.5 Sauvegardes

**Automatique** : chaque jour à 3 h (au réveil si le Mac dormait ; sautée s'il était
éteint). Installée par `install-native.sh`.

**Manuelle** :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./scripts/backup_db.sh
```

Vérification : la dernière ligne commence par `État :` et la ligne `OK : ministere-…duckdb`
indique le nombre de tables.

**Choisir une destination hors du disque du Mac** (recommandé : une panne du disque
interne emporterait sinon base et sauvegardes). Choisir **une** des deux commandes.

Disque externe (remplacer `MonDisque` par le nom du disque affiché dans le Finder) :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/install-native.sh --sauvegarde-vers "/Volumes/MonDisque/ministere-info-sauvegardes"
```

iCloud Drive :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/install-native.sh --sauvegarde-vers "$HOME/Library/Mobile Documents/com~apple~CloudDocs/ministere-info-sauvegardes"
```

Points d'attention :

- Disque externe débranché à 3 h : la sauvegarde est faite dans `<projet>/data/backups`
  (secours) et le journal l'indique (`destination indisponible`, code 5).
- iCloud Drive : environ 1 Go par sauvegarde, 7 sauvegardes conservées → environ 7 Go
  d'espace iCloud et autant de transferts. Désactiver « Optimiser le stockage du Mac »
  pour ce dossier n'est pas nécessaire pour la sauvegarde, mais une restauration exige
  que le fichier soit téléchargé (icône nuage dans le Finder).
- Le journal signale `ATTENTION : sauvegarde sur le même disque que la base` tant que la
  destination est sur le disque interne.

**Méthode** (détaillée en tête de `scripts/backup_db.sh`) : la base est ouverte en lecture
seule, ce qui pose un verrou partagé DuckDB (l'app continue de fonctionner, un ETL ne peut
pas démarrer pendant la copie) ; le fichier est copié, la copie est rouverte et comparée à
l'original (tables, vues, taille), puis renommée. Seules les sauvegardes de plus de
`BACKUP_RETENTION_DAYS` jours sont supprimées, et seulement après une copie réussie.

Codes de sortie : `0` succès · `2` base absente · `3` Python/duckdb absent (lancer
`uv sync --frozen`) · `4` ETL en cours ou copie invalide · `5` destination indisponible,
secours local utilisé · `6` espace disque insuffisant.

**Restaurer une sauvegarde** — 1) repérer la destination (ligne « Destination ») et la
sauvegarde voulue ; remplacer ci-dessous le chemin par la destination affichée :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/status.sh
ls -lh "/Volumes/MonDisque/ministere-info-sauvegardes"
```

2) Remplacer la base (ici par la sauvegarde du 1er octobre 2026 à 3 h, à adapter) :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/stop.sh
mv data/ministere.duckdb data/ministere.duckdb.avant-restauration
cp "/Volumes/MonDisque/ministere-info-sauvegardes/ministere-2026-10-01_0300.duckdb" data/ministere.duckdb
./deploy/native/start.sh
```

Cas rare : si un fichier du même nom terminé par `.wal` existe à côté de la sauvegarde,
le copier aussi, sous le nom `data/ministere.duckdb.wal`, avant `start.sh`.

Vérification : l'app répond et les pages affichent des données. Supprimer ensuite
`data/ministere.duckdb.avant-restauration` quand tout est vérifié.

### 2.6 Dépannage

| Symptôme | Diagnostic | Solution |
|---|---|---|
| `status.sh` : `NE RÉPOND PAS` | `tail -n 50 ~/Library/Logs/ministere-info/app.err.log` | Corriger l'erreur affichée, puis `./deploy/native/start.sh` |
| `Extension "spatial" not found` dans le journal | La version de DuckDB a changé | `./deploy/native/install-native.sh` (réinstalle l'extension ; Internet requis) |
| `Le port 8501 est déjà utilisé par : …` | Autre programme sur le port (souvent Docker pendant la transition) | Voir bascule, étape 8, ou choisir `--port 8502` |
| `Base introuvable ou vide` | Chemin de base erroné | `./deploy/native/status.sh`, puis `install-native.sh --base <chemin>` |
| L'ETL échoue avec `Could not set lock on file` | L'app lit la base | §2.4 |
| Le Terminal indique `Rosetta` | Terminal ouvert en mode Intel | Finder → Applications → Utilitaires → Terminal → Lire les informations → décocher « Ouvrir avec Rosetta » |
| Page sans données | Base vide ou ancienne | Contrôle des tables : §4.6 (même requête, lancée avec `uv run python`) |

---

## 3. Bascule Docker → natif (8 étapes)

Chaque étape se termine par une **vérification**. Ne passer à l'étape suivante que si la
vérification est bonne. En cas de doute, s'arrêter : rien n'est modifié côté Docker avant
l'étape 8, et Docker continue de fonctionner sur son port pendant toute la période d'essai.

### Étape 1 — Faire l'état des lieux

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
docker inspect ministere-info --format '{{range .Mounts}}{{.Type}}  {{.Source}}  ->  {{.Destination}}{{println}}{{end}}'
launchctl list | grep -i ministere
```

Noter :

- le **port** de Docker (colonne `PORTS`, normalement `8501`) ;
- la **base** utilisée par Docker (ligne qui finit par `-> /app/data`) :
  - `bind  /Users/…/.ministere-info/data` → installation par `deploy/install.sh` ;
  - `volume  ministere-info_duckdb-data` → `docker-compose.prod.yml` du projet ;
  - `bind  /Users/…/ministere-de-l-info/data` → compose de développement ;
- les agents `launchctl` présents (`com.ministere-info` = démarrage auto Docker ;
  `com.crocdeine.ministere-info.backup` = ancienne sauvegarde).

Vérification : ces trois informations sont notées. Si `docker` répond `Cannot connect
to the Docker daemon`, ouvrir OrbStack et recommencer. Si `docker inspect` répond
`No such object`, remplacer `ministere-info` par le nom affiché dans la colonne `NAMES`.

### Étape 2 — Choisir la base et en faire une copie de sécurité

L'app native lit par défaut la base du projet, celle que l'ETL met à jour :

```bash
cd ~/Documents/Docker/ministere-de-l-info
ls -lh data/ministere.duckdb
ls -lh ~/.ministere-info/data/ministere.duckdb 2>/dev/null
```

- Si la base du projet existe et est la plus récente (cas normal : l'ETL tourne dans le
  projet), ne rien changer.
- Si elle est absente ou plus ancienne que celle de `~/.ministere-info` (installation
  `install.sh` mise à jour par `update.sh`) :

  ```bash
  cd ~/Documents/Docker/ministere-de-l-info
  mv data/ministere.duckdb data/ministere.duckdb.ancienne 2>/dev/null
  cp -p ~/.ministere-info/data/ministere.duckdb data/ministere.duckdb
  ```

- Si Docker utilise le volume `ministere-info_duckdb-data` et que sa base est la plus
  récente, la récupérer :

  ```bash
  cd ~/Documents/Docker/ministere-de-l-info
  mv data/ministere.duckdb data/ministere.duckdb.ancienne 2>/dev/null
  docker run --rm -v ministere-info_duckdb-data:/data:ro -v "$PWD/data:/dest" alpine cp /data/ministere.duckdb /dest/ministere.duckdb
  ```

L'ancienne base du projet éventuelle est conservée sous `data/ministere.duckdb.ancienne`
(à supprimer après la bascule).

Copie de sécurité avant toute la suite (à supprimer après la bascule réussie) :

```bash
cd ~/Documents/Docker/ministere-de-l-info
cp -p data/ministere.duckdb ~/ministere-avant-bascule.duckdb
ls -lh data/ministere.duckdb ~/ministere-avant-bascule.duckdb
```

Vérification : les deux fichiers ont la même taille (environ 900 Mo à 1 Go).

### Étape 3 — Mettre à jour le code et vérifier uv

```bash
cd ~/Documents/Docker/ministere-de-l-info
git status
git pull
uv --version
```

- `git status` ne doit lister aucun fichier modifié (message `nothing to commit` ou
  `rien à valider`) ; sinon, demander à Claude Code avant de continuer.
- Si `uv --version` répond `command not found` :

  ```bash
  curl -LsSf https://astral.sh/uv/0.11.16/install.sh | sh
  ```

  puis fermer le Terminal, en rouvrir un et relancer `uv --version`.

Vérification : `ls deploy/native/` liste `install-native.sh` et `uv --version` affiche
un numéro de version.

### Étape 4 — Installer l'app native (port 8502, à côté de Docker)

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/install-native.sh
```

Le script affiche 9 étapes numérotées, puis ouvre le navigateur sur `http://localhost:8502`.
Durée : 1 à 3 minutes la première fois. Si Docker occupe déjà le port 8502 (cas où
`install.sh` avait trouvé 8501 pris), ajouter `--port 8503`.

Le script installe aussi la sauvegarde quotidienne ; il remplace l'ancien agent
`com.crocdeine.ministere-info.backup` (qui copiait le volume Docker) par la nouvelle
version, qui sauvegarde la base du projet. Docker n'est pas touché.

Vérification : le script se termine par `=== Installation native terminée ===` et
`./deploy/native/status.sh` indique `OK (répond)` sur la ligne `Santé`.

### Étape 5 — Comparer les deux versions

Ouvrir côte à côte `http://localhost:8501` (Docker) et `http://localhost:8502` (natif).
Parcourir les 5 pages (Accueil, Géographie, Élections, Économie, Législatif), en
particulier une carte par page.

Mémoire utilisée par l'app native :

```bash
ps -o rss=,command= -p "$(launchctl print gui/$(id -u)/com.crocdeine.ministere-info.native | awk '/^[[:space:]]*pid = /{print $3; exit}')"
```

(Premier nombre en kilo-octets ; à comparer avec `docker stats ministere-info --no-stream`.)

Vérification : les 5 pages s'affichent en natif, sans message d'erreur rouge. Différences
attendues : la version native contient les derniers développements (design system),
absents de l'image Docker de juin.

### Étape 6 — Tester la sauvegarde et la restauration

Brancher le disque de sauvegarde (ou choisir iCloud, §2.5), puis :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/install-native.sh --sauvegarde-vers "/Volumes/MonDisque/ministere-info-sauvegardes"
./scripts/backup_db.sh
```

Test de restauration **sans toucher à la base en service** :

```bash
cd ~/Documents/Docker/ministere-de-l-info
DERNIERE="$(ls -t "/Volumes/MonDisque/ministere-info-sauvegardes"/ministere-*.duckdb | head -n 1)"
echo "$DERNIERE"
.venv/bin/python -c "import duckdb, sys; c = duckdb.connect(sys.argv[1], read_only=True); print(c.execute(\"SELECT count(*) FROM duckdb_tables()\").fetchone()[0], 'tables')" "$DERNIERE"
```

Vérification : `backup_db.sh` affiche une ligne `OK : ministere-…duckdb`, sans
`ATTENTION : sauvegarde sur le même disque` ; le test de restauration affiche un nombre
de tables supérieur à 0.

### Étape 7 — Redémarrer le Mac

Menu Pomme → Redémarrer. Après l'ouverture de session, attendre une minute, puis :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/status.sh
```

Vérification : la ligne `Santé` indique `OK` sans avoir rien lancé à la main, et `http://localhost:8502`
s'ouvre.

---

> ## POINT D'ARRÊT — période de double fonctionnement (2 semaines)
>
> Utiliser la version native (`http://localhost:8502`) au quotidien pendant deux semaines,
> Docker restant disponible sur `http://localhost:8501`. Pendant cette période, avant un
> ETL : arrêter l'app native **et** Docker s'il lit la même base.
>
> Critères pour passer à l'étape 8 (validation explicite de Mathias) :
> - aucune indisponibilité inexpliquée de l'app native ;
> - `backup.log` montre une sauvegarde `OK` chaque jour où le Mac était allumé ;
> - au moins un redémarrage du Mac et un ETL réalisés sans incident.
>
> Ne pas exécuter l'étape 8 sans cette validation.

---

### Étape 8 — Bascule définitive : arrêter Docker, passer le natif sur 8501

1. Arrêter le conteneur, avec **une** des deux commandes selon l'étape 1.
   Installation `install.sh` (`~/.ministere-info`) :

   ```bash
   cd ~/.ministere-info && docker compose stop
   ```

   Compose du projet (`docker-compose.prod.yml`) :

   ```bash
   cd ~/Documents/Docker/ministere-de-l-info && docker compose -f docker-compose.prod.yml stop
   ```

   Utiliser `stop`, jamais `down -v` (qui supprimerait le volume de données).

2. Désactiver le démarrage automatique de Docker (sans le supprimer) :

   ```bash
   launchctl bootout gui/$(id -u)/com.ministere-info 2>/dev/null; echo "déchargé"
   mkdir -p ~/Library/LaunchAgents/desactives
   mv ~/Library/LaunchAgents/com.ministere-info.plist ~/Library/LaunchAgents/desactives/ 2>/dev/null; echo "déplacé"
   ```

3. Passer l'app native sur le port habituel :

   ```bash
   cd ~/Documents/Docker/ministere-de-l-info
   ./deploy/native/install-native.sh --port 8501
   ```

4. OrbStack : menu OrbStack → Settings → General → décocher « Start at login », puis
   quitter OrbStack. **Ne pas le désinstaller** : il reste le repli pendant encore un mois.

Vérification : `./deploy/native/status.sh` affiche `http://localhost:8501`, la ligne `Santé` indique `OK`
et `Démarrage auto Docker : inactif` ; après un redémarrage du Mac, l'app répond sur 8501
alors qu'OrbStack n'est pas lancé. La copie `~/ministere-avant-bascule.duckdb` peut alors
être supprimée.

### Retour arrière (à tout moment)

Retirer l'app native (base et sauvegardes conservées), puis réactiver Docker :

```bash
cd ~/Documents/Docker/ministere-de-l-info
./deploy/native/uninstall-native.sh
mv ~/Library/LaunchAgents/desactives/com.ministere-info.plist ~/Library/LaunchAgents/ 2>/dev/null
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ministere-info.plist
open -a OrbStack
```

Puis, après une minute, `cd ~/.ministere-info && docker compose up -d` (installation
`install.sh`) ou `docker compose -f docker-compose.prod.yml up -d` depuis le projet.

La base n'est modifiée ni par la bascule ni par le retour arrière. Attention : si Docker
utilise une autre base que le projet (`~/.ministere-info/data` ou volume), les mises à jour
faites en natif entre-temps n'y figurent pas.

---

## 4. Mode Docker / OrbStack (repli, distribution)

Ce mode reste fonctionnel. Il sert de repli pendant la transition et de canal de
distribution pour un éventuel tiers (`deploy/install.sh`, voir `deploy/README-deploy.md`).
Deux configurations existent :

> **Dev vs prod — deux comportements différents pour `/app/data`** :
> - **Dev** (`docker-compose.yml`) : bind mount `./data:/app/data:ro` — la base locale est
>   visible immédiatement dans le conteneur, sans reconstruction ni copie.
> - **Prod** (`docker-compose.prod.yml`) : volume nommé `duckdb-data`
>   (`ministere-info_duckdb-data`) — la base est copiée une fois dans le volume.

Prérequis : hôte Docker (OrbStack, Docker Desktop, Colima), 4 Go de RAM, 3 Go de disque,
arm64 ou x86_64. Réseau requis au `docker build` seulement.

### 4.1 Premier déploiement (prod)

```bash
docker build -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up --no-start
docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v "$(pwd)/data:/source:ro" \
  alpine cp /source/ministere.duckdb /data/
docker compose -f docker-compose.prod.yml up -d
curl http://localhost:8501/_stcore/health
```

La dernière commande doit répondre `ok`.

Sans base locale : `./scripts/download_db.sh` (release la plus récente contenant
`ministere.duckdb.gz`, `GITHUB_TOKEN` requis dans `.env`), ou exécution de l'ETL sur
l'hôte (`uv sync --frozen --group etl`, puis les scripts `scripts/etl_*.py` et `load_*.py`).
L'ETL s'exécute toujours sur l'hôte, jamais dans le conteneur.

### 4.2 Opérations

| Action | Commande |
|---|---|
| Journaux | `docker compose -f docker-compose.prod.yml logs -f` |
| Arrêt (préserve le volume) | `docker compose -f docker-compose.prod.yml stop` |
| Démarrage | `docker compose -f docker-compose.prod.yml up -d` |
| Mise à jour du code | `git pull && docker build -t ministere-info:latest . && docker compose -f docker-compose.prod.yml up -d --force-recreate` |

Rafraîchir les données : arrêter le conteneur, lancer l'ETL sur l'hôte, recopier
`data/ministere.duckdb` dans le volume (commande `docker run … alpine cp` du §4.1),
redémarrer.

### 4.3 Sauvegardes en mode Docker

`scripts/backup_db.sh` sauvegarde le fichier désigné par `MINISTERE_DB_PATH` (§2.5), pas le
contenu d'un volume Docker. Pour l'installation `install.sh`, dont la base est un fichier
de l'hôte :

```bash
cd ~/Documents/Docker/ministere-de-l-info
MINISTERE_DB_PATH="$HOME/.ministere-info/data/ministere.duckdb" ./scripts/backup_db.sh
```

Pour le volume `ministere-info_duckdb-data`, copier d'abord la base hors du volume
(commande `docker run … alpine cp` de l'étape 2 de la bascule), puis sauvegarder ce fichier.

Restauration dans le volume :

```bash
docker compose -f docker-compose.prod.yml stop
docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v "/chemin/des/sauvegardes:/backup:ro" \
  alpine cp /backup/ministere-2026-10-01_0300.duckdb /data/ministere.duckdb
docker compose -f docker-compose.prod.yml up -d
```

### 4.4 Arrêter Docker après la période de transition

Procédure : étape 8 de la bascule (§3). Plus tard, sur décision (pas avant un mois de
fonctionnement natif sans incident), l'espace disque peut être récupéré :

```bash
docker images | grep ministere
docker volume ls | grep ministere
```

(Images d'environ 1,15 Go chacune, et volume de données.)

La suppression (`docker image rm …`, `docker volume rm ministere-info_duckdb-data`,
désinstallation d'OrbStack) est irréversible : la faire seulement après avoir vérifié que
la base du projet et ses sauvegardes sont à jour.

### 4.5 Publication de la base

Toujours via le script, voir [`deploy/README-deploy.md`](../deploy/README-deploy.md)
(convention d'empreinte : SHA256 de l'archive `.gz`) :

```bash
./scripts/publish_db.sh v0.X-description
gh release upload v0.X-description --clobber data/ministere.duckdb.gz data/ministere.duckdb.gz.sha256
```

### 4.6 Dépannage Docker

| Symptôme | Cause / diagnostic | Solution |
|---|---|---|
| `Extension "spatial" not found` | Image construite sans `INSTALL spatial` | `docker build --no-cache …` puis `up -d --force-recreate` |
| Conteneur jamais `healthy` | `docker compose -f docker-compose.prod.yml logs --tail 50` ; port pris (`lsof -i :8501`) | Corriger l'erreur ; libérer le port |
| Redémarrage en boucle | Erreur Python fatale au démarrage | `docker compose … stop`, lire les journaux, corriger |
| Pages absentes du menu | Image antérieure au commit `d7658a2` (`pages/` non copié) | Reconstruire l'image |
| `.env` absent | Référencé par `env_file` | `cp .env.example .env` |
| Base absente après redémarrage | Volume supprimé par `down -v` | Réinitialiser le volume (§4.1) ; ne jamais utiliser `down -v` |

Contrôle du contenu de la base (Docker) :

```bash
docker exec ministere-info python -c "
import duckdb
con = duckdb.connect('/app/data/ministere.duckdb', read_only=True)
con.execute('LOAD spatial')
for t in ['geographies_regions', 'geographies_communes', 'populations']:
    print(t, con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
"
```

Attendu : `geographies_regions` 18, `geographies_communes` 34877, `populations` ≥ 34858.
En natif, la même requête se lance depuis le projet avec `uv run python -c "…"` en
remplaçant le chemin par `data/ministere.duckdb`.

### 4.7 Variables d'environnement (Docker)

| Variable | Valeur prod | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Niveau de journalisation |
| `LOG_FORMAT` | `json` | Format des journaux |
| `APP_ENV` | `production` | Environnement applicatif |
| `STREAMLIT_SERVER_RUN_ON_SAVE` | `false` | Rechargement automatique désactivé |
