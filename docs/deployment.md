# Déploiement et exploitation

Deux modes d'exécution coexistent :

| Mode | Rôle | Référence |
|---|---|---|
| **Natif** (uv + LaunchAgent macOS) | **Mode principal**, seul mode réellement installé sur le Mac mini de Mathias | [ADR-0012](adr/0012-execution-native-mac.md), §1 à §3 |
| **Docker / OrbStack** | Non déployé actuellement (constat du 25/09/2026) ; conservé comme repli possible et pour la distribution à d'éventuels tiers (`deploy/install.sh`) | §4 |

La publication des releases (image + base) est décrite dans
[`deploy/README-deploy.md`](../deploy/README-deploy.md).

Convention de ce document : les blocs de commandes se copient-collent tels quels dans
le Terminal. Ils ne contiennent volontairement aucun commentaire `#` : le Terminal de
macOS utilise zsh, qui par défaut transmet un `# commentaire` comme argument de la
commande au lieu de l'ignorer. Les exemples utilisent une variable `PROJET` définie une
fois en tête de session — **toujours entre guillemets**, y compris pour `cd`, car le
chemin réel (25/09/2026 : `/Volumes/le gros stockage/ministere-de-l-info`, sur un
disque externe) contient des espaces :

```bash
PROJET="/Volumes/le gros stockage/ministere-de-l-info"
```

Adapter cette ligne si le projet est ailleurs, puis copier les blocs suivants tels quels.

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
- **Projet sur disque externe (constat du 25/09/2026)** : le script réellement lancé
  par le LaunchAgent (`~/.config/ministere-info/lancer-app.sh`, généré par
  `install-native.sh`) est toujours installé sur le disque interne, pour rester
  exécutable même si le disque du projet n'est pas encore monté à l'ouverture de
  session. Il attend le montage jusqu'à 60 secondes (message clair dans
  `app.err.log`), puis démarre Streamlit une fois le projet disponible. **Limite** :
  si le disque reste débranché plus de 60 secondes, l'application reste indisponible
  jusqu'au prochain cycle de relance (`KeepAlive`, au rythme de `ThrottleInterval`) ou
  jusqu'à `./deploy/native/start.sh` une fois le disque rebranché.

### Fichiers et emplacements

| Élément | Emplacement |
|---|---|
| Scripts | `<projet>/deploy/native/` : `install-native.sh`, `start.sh`, `stop.sh`, `status.sh`, `uninstall-native.sh` |
| Configuration enregistrée | `~/.config/ministere-info/native.conf` (projet, base, port, sauvegarde) |
| LaunchAgent application | `~/Library/LaunchAgents/com.crocdeine.ministere-info.native.plist` (généré depuis `deploy/native/ministere-info.plist`) |
| Script lancé par ce LaunchAgent | `~/.config/ministere-info/lancer-app.sh` (disque interne ; généré depuis `deploy/native/lancer-app.sh`, attend le montage du disque du projet) |
| LaunchAgent sauvegarde | `~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist` (généré depuis `scripts/com.crocdeine.ministere-info.backup.plist`) |
| Anciens LaunchAgents désactivés | `~/Library/LaunchAgents/desactives/` (archivés par `install-native.sh`, jamais supprimés) |
| Journaux | `~/Library/Logs/ministere-info/` : `app.err.log`, `app.out.log`, `backup.log` (visibles dans l'app Console) |
| Base | `MINISTERE_DB_PATH`, défaut `<projet>/data/ministere.duckdb` |
| Sauvegardes | `BACKUP_DEST`, défaut `<projet>/data/backups/` (à remplacer par un disque externe, voir §2.5) |

### Variables

| Variable | Défaut | Utilisée par |
|---|---|---|
| `MINISTERE_DB_PATH` | `<projet>/data/ministere.duckdb` | application (`src/ministere_de_l_info/config.py`), sauvegarde |
| `MINISTERE_PORT` | `8501` | `install-native.sh` |
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
cd "$PROJET"
./deploy/native/status.sh
```

Vérification : la ligne `Santé` indique `OK (répond)` ; la section « Sauvegardes » donne la date de la dernière
sauvegarde. L'app est à l'adresse indiquée (`http://localhost:8501`).

### 2.2 Arrêter, démarrer, redémarrer

Arrêter (jusqu'au prochain `start.sh` ou à la prochaine ouverture de session) :

```bash
cd "$PROJET"
./deploy/native/stop.sh
```

Démarrer, ou redémarrer si l'app tourne déjà :

```bash
cd "$PROJET"
./deploy/native/start.sh
```

### 2.3 Mettre à jour le code

```bash
cd "$PROJET"
git pull
./deploy/native/install-native.sh
```

`install-native.sh` est idempotent : il resynchronise les dépendances (`uv sync --frozen`),
réinstalle l'extension spatial si la version de DuckDB a changé, puis redémarre l'app avec
les paramètres enregistrés.

### 2.4 Lancer un ETL (écriture dans la base)

DuckDB n'accepte aucun écrivain tant qu'un programme lit la base. Il faut donc arrêter
l'app (et un éventuel conteneur Docker s'il lit le même fichier, en repli). Exemple avec
`load_economie.py`, à remplacer par le script ETL voulu :

```bash
cd "$PROJET"
./deploy/native/stop.sh
uv run python scripts/load_economie.py
./deploy/native/start.sh
```

Si l'ETL affiche `Could not set lock on file`, un programme lit encore la base : vérifier
`./deploy/native/status.sh` (et `docker ps`, si Docker est un jour redéployé en repli).
Une sauvegarde lancée pendant un ETL s'abandonne d'elle-même (code 4) sans rien abîmer.

### 2.5 Sauvegardes

**Automatique** : chaque jour à 3 h (au réveil si le Mac dormait ; sautée s'il était
éteint). Installée par `install-native.sh`.

**Manuelle** :

```bash
cd "$PROJET"
./scripts/backup_db.sh
```

Vérification : la dernière ligne commence par `État :` et la ligne `OK : ministere-…duckdb`
indique le nombre de tables.

**Choisir une destination hors du disque du Mac** (recommandé : une panne du disque
interne emporterait sinon base et sauvegardes). Choisir **une** des deux commandes.

Disque externe (remplacer `MonDisque` par le nom du disque affiché dans le Finder) :

```bash
cd "$PROJET"
./deploy/native/install-native.sh --sauvegarde-vers "/Volumes/MonDisque/ministere-info-sauvegardes"
```

iCloud Drive :

```bash
cd "$PROJET"
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
cd "$PROJET"
./deploy/native/status.sh
ls -lh "/Volumes/MonDisque/ministere-info-sauvegardes"
```

2) Remplacer la base (ici par la sauvegarde du 1er octobre 2026 à 3 h, à adapter) :

```bash
cd "$PROJET"
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
| `Le port 8501 est déjà utilisé par : …` | Autre programme sur le port | Arrêter ce programme, ou choisir `--port 8502` |
| `Base introuvable ou vide` | Chemin de base erroné, ou disque externe débranché | `./deploy/native/status.sh`, puis `install-native.sh --base <chemin>` |
| L'ETL échoue avec `Could not set lock on file` | L'app lit la base | §2.4 |
| Le Terminal indique `Rosetta` | Terminal ouvert en mode Intel | Finder → Applications → Utilitaires → Terminal → Lire les informations → décocher « Ouvrir avec Rosetta » |
| Page sans données | Base vide ou ancienne | Contrôle des tables : §4.6 (même requête, lancée avec `uv run python`) |
| L'app ne démarre pas après l'ouverture de session, `app.err.log` indique « indisponible après … » | Le disque externe n'était pas encore monté quand le LaunchAgent a démarré (voir §1, limite connue) | Rebrancher/monter le disque, puis `./deploy/native/start.sh` |

---

## 3. Installation directe (pas de Docker sur le Mac)

Constat du 25/09/2026 : aucun conteneur ni image Docker de l'application n'existe sur
le Mac mini. La période de double fonctionnement natif/Docker prévue par l'ADR-0012
(§8 de la version précédente de cette section) n'a plus d'objet : il n'y a rien à
comparer ni à basculer. L'installation se fait **directement sur le port 8501**.

Chaque étape se termine par une **vérification**. Ne passer à l'étape suivante que si
la vérification est bonne.

> ## POINT D'ARRÊT — avant l'étape 5 (suppression de l'ancien agent de sauvegarde)
>
> `install-native.sh` détecte automatiquement un ancien LaunchAgent de sauvegarde en
> échec et le range dans `~/Library/LaunchAgents/desactives/` (rien n'est supprimé).
> Vérifier le contenu de ce dossier après l'étape 5 avant de continuer, et ne rien
> supprimer manuellement (ni cet ancien plist, ni une base, ni une sauvegarde) sans
> validation explicite de Mathias en chat.

### Étape 1 — Constater l'absence de Docker

```bash
docker ps 2>&1
launchctl list | grep -i ministere
```

Attendu : soit `docker` répond « Cannot connect to the Docker daemon » (ou n'est pas
installé), soit `docker ps` ne montre aucun conteneur `ministere-info`. `launchctl list`
peut montrer `com.crocdeine.ministere-info.backup` (l'ancienne sauvegarde en échec,
traitée à l'étape 5).

Si un conteneur `ministere-info` tourne réellement, s'arrêter ici et prévenir le
directeur : ce document suppose qu'il n'y en a pas (cas contraire : reprendre l'ancienne
procédure de bascule en récupérant la version de cette section dans l'historique Git).

Vérification : pas de conteneur `ministere-info` actif.

### Étape 2 — Localiser le projet et la base, copie de sécurité

```bash
PROJET="/Volumes/le gros stockage/ministere-de-l-info"
ls -lh "$PROJET/data/ministere.duckdb"
```

Si ce fichier n'existe pas ou semble trop ancien (comparer avec la date attendue de la
dernière mise à jour), s'arrêter et vérifier avec le directeur avant de continuer —
`install-native.sh` refuse de démarrer sans base valide, mais autant le savoir avant.

Copie de sécurité (à conserver jusqu'à la fin de l'étape 6, sur un support qui n'est
**pas** le disque du projet si possible, par exemple le disque interne) :

```bash
cp -p "$PROJET/data/ministere.duckdb" ~/ministere-avant-installation-native.duckdb
ls -lh "$PROJET/data/ministere.duckdb" ~/ministere-avant-installation-native.duckdb
```

Vérification : les deux fichiers ont la même taille.

### Étape 3 — Code à jour et `uv` installé

```bash
cd "$PROJET"
git status
git pull
uv --version
```

- `git status` ne doit lister aucun fichier modifié.
- Si `uv --version` répond `command not found` :

  ```bash
  curl -LsSf https://astral.sh/uv/0.11.16/install.sh | sh
  ```

  puis fermer le Terminal, en rouvrir un et relancer `uv --version`.

Vérification : `ls deploy/native/` liste `install-native.sh` et `uv --version` affiche
un numéro de version.

### Étape 4 — Vérifier que le port 8501 est libre

```bash
lsof -nP -iTCP:8501 -sTCP:LISTEN 2>/dev/null || echo "port 8501 libre"
```

Si un programme occupe déjà le port 8501, l'identifier et l'arrêter (ou installer avec
`--port 8502` à titre temporaire, puis reprendre plus tard sur 8501).

Vérification : `port 8501 libre` s'affiche, ou l'occupant est identifié et traité.

### Étape 5 — Installer l'application native

```bash
cd "$PROJET"
./deploy/native/install-native.sh
```

Le script affiche 9 étapes numérotées. S'il détecte un ancien LaunchAgent de sauvegarde
en échec (script disparu, ex. ancien chemin `~/Documents/...`), il affiche
`Ancien agent de sauvegarde détecté (...) — désactivé` et le range dans
`~/Library/LaunchAgents/desactives/` avant d'installer la nouvelle version. **Voir le
POINT D'ARRÊT ci-dessus avant de continuer.**

Le script se termine par l'ouverture du navigateur sur `http://localhost:8501`.
Durée : 1 à 3 minutes la première fois.

Vérification : le script se termine par `=== Installation native terminée ===`,
`./deploy/native/status.sh` indique `OK (répond)` sur la ligne `Santé`, et le dossier
`~/Library/LaunchAgents/desactives/` contient l'ancien plist de sauvegarde s'il y en
avait un (vérifié au POINT D'ARRÊT).

### Étape 6 — Régler et tester la sauvegarde

Sauvegarde vers un disque différent de celui du projet (recommandé — voir §2.5 pour le
détail) :

```bash
cd "$PROJET"
./deploy/native/install-native.sh --sauvegarde-vers "/Volumes/MonAutreDisque/ministere-info-sauvegardes"
./scripts/backup_db.sh
```

Test de restauration **sans toucher à la base en service** :

```bash
cd "$PROJET"
DERNIERE="$(ls -t "/Volumes/MonAutreDisque/ministere-info-sauvegardes"/ministere-*.duckdb | head -n 1)"
echo "$DERNIERE"
.venv/bin/python -c "import duckdb, sys; c = duckdb.connect(sys.argv[1], read_only=True); print(c.execute(\"SELECT count(*) FROM duckdb_tables()\").fetchone()[0], 'tables')" "$DERNIERE"
```

Vérification : `backup_db.sh` affiche une ligne `OK : ministere-…duckdb` ; le test de
restauration affiche un nombre de tables supérieur à 0. Si la sauvegarde est sur le
même disque que le projet (cas du 25/09 si aucun autre disque n'est disponible), le
journal l'indique (`ATTENTION : sauvegarde sur le même disque`) — accepté en attendant
un second disque, mais à corriger dès que possible (voir recommandation §2.5).

### Étape 7 — Redémarrage de contrôle

Menu Pomme → Redémarrer. Après l'ouverture de session (et le montage du disque externe
si le projet y est installé — laisser une minute de plus que d'habitude), lancer :

```bash
cd "$PROJET"
./deploy/native/status.sh
```

Vérification : la ligne `Santé` indique `OK` sans avoir rien relancé à la main, et
`http://localhost:8501` s'ouvre. Si `status.sh` indique `NE RÉPOND PAS` juste après le
redémarrage, regarder `~/Library/Logs/ministere-info/app.err.log` : un message
« indisponible après 60s » signale que le disque externe n'était pas monté à temps
(voir §1, limite connue) — remonter le disque puis `./deploy/native/start.sh`.

### Retour arrière

Retirer l'app native (base et sauvegardes conservées) :

```bash
cd "$PROJET"
./deploy/native/uninstall-native.sh
```

La base n'est modifiée ni par l'installation ni par le retrait. La copie de sécurité de
l'étape 2 (`~/ministere-avant-installation-native.duckdb`) peut être supprimée une fois
l'étape 7 validée.

---

## 4. Mode Docker / OrbStack (repli, distribution)

Ce mode reste fonctionnel mais **n'est pas déployé actuellement** (constat du
25/09/2026 : aucun conteneur ni image sur le Mac mini). Il sert de repli possible et de
canal de distribution pour un éventuel tiers (`deploy/install.sh`, voir
`deploy/README-deploy.md`). Deux configurations existent :

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
cd "$PROJET"
MINISTERE_DB_PATH="$HOME/.ministere-info/data/ministere.duckdb" ./scripts/backup_db.sh
```

Pour le volume `ministere-info_duckdb-data`, copier d'abord la base hors du volume
(commande `docker run … alpine cp` du §4.1, sens inverse), puis sauvegarder ce fichier.

Restauration dans le volume :

```bash
docker compose -f docker-compose.prod.yml stop
docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v "/chemin/des/sauvegardes:/backup:ro" \
  alpine cp /backup/ministere-2026-10-01_0300.duckdb /data/ministere.duckdb
docker compose -f docker-compose.prod.yml up -d
```

### 4.4 Si Docker est un jour redéployé puis retiré

Sans objet le 25/09/2026 (aucun conteneur Docker installé). Si Docker est un jour
redéployé en repli puis retiré : arrêter le conteneur (`docker compose ... stop`,
jamais `down -v`), décharger son LaunchAgent
(`launchctl bootout gui/$(id -u)/com.ministere-info`, plist à archiver dans
`~/Library/LaunchAgents/desactives/`), puis, sur décision, récupérer l'espace disque :

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
