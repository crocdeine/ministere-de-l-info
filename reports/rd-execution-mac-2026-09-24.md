# R&D — Mode d'exécution de l'application sur Mac

**Date** : 2026-09-24
**Auteur** : agent « R&D déploiement Mac » (session cloud Claude Code)
**Nature** : étude, aucune modification de code. Aucune décision prise : ce document **propose**, Mathias décide.
**Hors périmètre** : correction des checksums et unification des Dockerfiles (traitées par un autre agent en parallèle).

---

## Résumé exécutif

1. Docker/OrbStack fonctionne, mais ajoute une couche (une petite machine virtuelle Linux) qui n'apporte presque rien à une app **mono-utilisateur, locale**, dont l'ETL tourne **déjà nativement** sur le Mac avec uv.
2. Constat clé : l'app en fonctionnement n'utilise **ni GeoPandas ni GDAL** (ils sont dans le groupe `etl` de `pyproject.toml`) ; ses seules dépendances « délicates » (DuckDB, extension `spatial`, pyarrow, polars) existent toutes en version Mac Apple Silicon officielle — l'obstacle technique habituel du natif n'existe pas ici.
3. Recommandation : **option B — exécution native avec uv, lancée par un LaunchAgent macOS**, avec l'image Docker conservée comme solution de repli pendant la transition.
4. Gains attendus : un seul environnement (Mac = dev = exécution = CI), démarrage en quelques secondes, pas de machine virtuelle, sauvegardes par simple copie de fichier, disparition de la question « quel Dockerfile ? ».
5. Coût : ~6 à 10 fichiers à créer/modifier (dont 4 fichiers Python pour rendre le chemin de la base configurable), migration testable en parallèle de l'existant, réversible.

---

## 1. Glossaire minimal

| Terme | En une phrase |
|---|---|
| **Docker / conteneur** | Une « boîte » qui contient l'app et tout ce dont elle a besoin, exécutée à l'intérieur d'un mini-Linux. |
| **OrbStack** | Le logiciel qui fait tourner ce mini-Linux (une machine virtuelle) sur le Mac pour pouvoir lancer des conteneurs. |
| **Image (ghcr.io)** | Le « modèle » de la boîte, fabriqué par GitHub Actions et téléchargé depuis le registre GitHub. |
| **Natif** | L'app tourne directement sur macOS, sans boîte ni machine virtuelle. |
| **uv** | L'outil qui installe Python et les bibliothèques exactes listées dans `uv.lock`, déjà utilisé pour l'ETL et les tests. |
| **launchd / LaunchAgent** | Le mécanisme de macOS qui lance un programme automatiquement à l'ouverture de session et le relance s'il plante (décrit par un petit fichier `.plist`). |
| **Extension `spatial`** | Module complémentaire de DuckDB pour les calculs géographiques, téléchargé une fois puis stocké dans `~/.duckdb/extensions/`. |
| **Notarisation** | Validation d'une application par Apple ; sans elle, macOS affiche « développeur non identifié » à l'ouverture. |

---

## 2. Situation actuelle (constatée dans le dépôt)

| Élément | Fichier | Constat |
|---|---|---|
| Distribution | `deploy/install.sh` | Homebrew → OrbStack → `~/.ministere-info/` → DB depuis la dernière release → `docker compose up` → LaunchAgent `com.ministere-info` (`RunAtLoad`, script `start.sh` qui attend Docker 60 s). |
| Compose utilisateur | `deploy/docker-compose.yml` | Image `ghcr.io/crocdeine/ministere-de-l-info:latest`, **bind mount** de `~/.ministere-info/data`, port publié `8501:8501` (donc sur toutes les interfaces réseau du Mac). |
| Compose prod local | `docker-compose.prod.yml` | **Named volume** `ministere-info_duckdb-data`, limite 2 Go RAM. |
| Sauvegardes | `scripts/backup_db.sh` + plist | Copie **depuis le named volume** de `docker-compose.prod.yml`, pas depuis `~/.ministere-info/data` d'`install.sh` ; destination `data/backups/` sur le **même disque** ; chemins en dur `/Users/crocdeine/Documents/Docker/...`. |
| Chemin de la base | `viz/elections_queries.py`, `viz/economie_queries.py`, `viz/legislatif_queries.py`, `pages/1_📍_Géographie.py` | Codé en dur, relatif au dossier du code (`parents[3] / "data" / "ministere.duckdb"`) ; aucune variable de configuration. |
| Extension spatial | mêmes fichiers | Les pages font `LOAD spatial` **sans** `INSTALL` : l'extension doit être préinstallée (dans l'image Docker, ou sur le Mac par un premier passage de l'ETL via `etl/_common.py`). |
| Dépendances runtime | `pyproject.toml` | `geopandas`/`openpyxl` uniquement dans le groupe `etl` ; aucun `import geopandas` dans `src/` hors ETL, `pages/` et `app.py` (vérifié par recherche). |
| Wheels Mac arm64 | `uv.lock` | Présents pour duckdb 1.5.2, pyarrow 24, polars, shapely, pyproj, pyogrio (GDAL embarqué). |
| Hot reload | `.streamlit/config.toml` | `runOnSave = true` : pratique en dev, indésirable pour l'app « de tous les jours ». |

**Point à vérifier sur le Mac mini** (non vérifiable depuis le cloud) : quelle configuration tourne réellement — `~/.ministere-info` (install.sh) ou `docker-compose.prod.yml` dans le dossier du projet ? Selon la réponse, la sauvegarde automatique actuelle **ne sauvegarde peut-être rien d'utile**.

---

## 3. Options étudiées

### A. Statu quo Docker/OrbStack

- **Pour** : déjà en place et testé (macOS 26.4.1) ; isolation de l'app ; extension spatial figée dans l'image ; redémarrage automatique et healthcheck.
- **Contre** :
  - Trois environnements différents à maintenir cohérents : Mac (ETL avec uv), conteneur Debian (app), Ubuntu (CI) — plus deux Dockerfiles divergents (§3.4 de l'état des lieux).
  - Surcoût mémoire de la machine virtuelle : OrbStack annonce ~0,1 % CPU au repos et une mémoire allouée dynamiquement, avec 150–300 Mo au repos selon des comparatifs tiers ([OrbStack FAQ](https://docs.orbstack.dev/faq), [OrbStack Efficiency](https://docs.orbstack.dev/efficiency), [sliplane.io](https://sliplane.io/blog/orbstack-vs-docker)). Faible, mais non nul, et s'ajoute à ~1,15 Go d'image sur disque.
  - Chaîne de mise à jour longue : tag → GitHub Actions construit l'image multi-arch → `docker compose pull`. La dernière image date de v0.5 (25 juin) : le design system n'y est pas.
  - Sauvegarde et mise à jour de la base passent par des manipulations de volumes Docker, peu lisibles pour un novice.
  - DuckDB n'autorise qu'un seul processus écrivain ([DuckDB — Concurrency](https://duckdb.org/docs/current/connect/concurrency)) : il faut de toute façon arrêter l'app avant l'ETL, et le verrouillage de fichier à travers la frontière machine virtuelle ↔ macOS n'est pas garanti — risque de lecture d'une base à moitié écrite si on oublie.
  - Licence : OrbStack est gratuit pour un usage personnel, payant en usage commercial ([OrbStack Licensing](https://docs.orbstack.dev/licensing)) — sans impact aujourd'hui, à garder en tête si le projet devenait professionnel.

### B. Natif uv + LaunchAgent (recommandé)

Principe : `uv run --frozen --no-dev streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.runOnSave false`, lancé par un LaunchAgent avec `RunAtLoad` + `KeepAlive` (relance si plantage) ([launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html), [Apple — Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)).

- **Pour** :
  - Un seul outil (uv) et un seul fichier de versions (`uv.lock`) pour le Mac, la CI et les sessions cloud de Claude Code. uv installe lui-même Python 3.12 (binaires arm64 autonomes, sans droits administrateur) ([uv — Installing Python](https://docs.astral.sh/uv/guides/install-python/)).
  - DuckDB : wheel officiel `macosx_11_0_arm64` ; extension `spatial` distribuée pour la plateforme `osx_arm64`, stockée dans `~/.duckdb/extensions/v1.5.2/osx_arm64/`, signée, et installable hors ligne depuis un fichier local (`INSTALL '/chemin/spatial.duckdb_extension'`) ([DuckDB — Installing Extensions](https://duckdb.org/docs/current/extensions/installing_extensions)). C'est **déjà le cas** sur le Mac puisque l'ETL fait `INSTALL spatial` en natif.
  - GDAL/GeoPandas : sans objet à l'exécution ; pour l'ETL, pyogrio embarque GDAL dans son wheel arm64 (déjà utilisé aujourd'hui).
  - Démarrage : mesure indicative dans le conteneur cloud (Linux, sans base) : Streamlit répond au healthcheck en **1,5 s**, ~75 Mo de mémoire avant la première page. Sur le M4, attendre quelques secondes, contre ~30 s à 60 s aujourd'hui (démarrage OrbStack + conteneur).
  - Sauvegarde = copie d'un fichier normal ; lisible dans le Finder ; compatible Time Machine.
  - Écoute sur `127.0.0.1` uniquement : l'app n'est plus visible depuis le réseau local (aujourd'hui `8501:8501` l'expose sur le Wi-Fi).
- **Contre** :
  - Pas d'isolation : l'app tourne avec les droits de la session de Mathias (risque faible : code et dépendances maîtrisés, versions et empreintes figées par `uv.lock`).
  - Une mise à jour de DuckDB change le dossier d'extension → il faut refaire `INSTALL spatial` (à intégrer dans le script de mise à jour ; les pages actuelles plantent sinon).
  - Si l'app tourne depuis le dossier de dev, chaque modification faite par Claude Code est immédiatement visible (voir question 2).
  - Commandes `launchctl` peu intuitives → à envelopper dans un petit script (`start`/`stop`/`status`/`logs`).

### C. Application Mac empaquetée

| Variante | Faisabilité réelle |
|---|---|
| **PyInstaller / py2app / Briefcase + pywebview** (ex. [streamlit-desktop-app](https://github.com/ohtaman/streamlit-desktop-app)) | Techniquement possible (DuckDB = un seul fichier `.so`, GeoPandas inutile à l'exécution), mais : Streamlit se prête mal au gel (fichiers statiques et métadonnées à déclarer à la main, [discussion Streamlit](https://discuss.streamlit.io/t/using-pyinstaller-or-similar-to-create-an-executable/902)) ; extension `spatial` à embarquer et installer depuis le fichier ; app de plusieurs centaines de Mo à **reconstruire intégralement** à chaque correction ; signature + notarisation Apple (programme développeur payant) sinon avertissement Gatekeeper ; nécessite une CI sur runner macOS. L'ETL resterait de toute façon en uv. |
| **stlite / @stlite/desktop** (Streamlit dans Pyodide/WebAssembly) | **Non faisable** : les paquets à extensions binaires non compilées pour Pyodide ne s'installent pas, et le système de fichiers est virtuel, déconnecté du disque ([stlite README](https://github.com/whitphx/stlite)) ; une base de 900 Mo + l'extension spatial dans la mémoire d'un onglet (~2 Go pratiques) est irréaliste. |
| **Tauri / Electron avec Python en « sidecar »** | Cumule les inconvénients de PyInstaller + une chaîne Rust/JavaScript, contraire à l'ADR-0002 (un seul langage). |

Alternative légère qui donne l'expérience « application » sans empaquetage : dans Safari (macOS 14+), *Fichier → Ajouter au Dock* sur `http://localhost:8501` crée une icône qui ouvre l'app dans sa propre fenêtre. Compatible avec A et B.

### D. Hébergement (signalé seulement)

Streamlit Community Cloud : 690 Mo à 2,7 Go de RAM, une seule app privée ([Streamlit Docs — resource limits](https://docs.streamlit.io/knowledge-base/deploy/resource-limits)) ; la base de 900 Mo n'entre pas dans Git et devrait être téléchargée à chaque démarrage. Un NAS/VPS supposerait un serveur, de l'authentification et de la maintenance. Contraire au choix « local, fichier unique, sans serveur » (ADR-0001/0002). À ne reconsidérer que si le besoin de partager l'app avec d'autres apparaît.

---

## 4. Tableau comparatif noté

Notes de 1 (mauvais) à 5 (excellent), non pondérées. D non noté (hors cadre).

| Critère | A. Docker/OrbStack | B. Natif uv + launchd | C. App empaquetée |
|---|:-:|:-:|:-:|
| Simplicité pour Mathias | 3 | 4 | 2 |
| Fiabilité | 4 | 4 | 2 |
| RAM / CPU (Mac mini M4) | 3 | 5 | 4 |
| Disque | 2 (image ~1,15 Go + VM) | 4 (env. ~0,6–0,9 Go) | 3 |
| Temps de démarrage | 3 (30–60 s) | 5 (quelques s) | 3 |
| Mises à jour du code | 3 | 4 | 1 |
| Mises à jour des données | 3 | 4 | 3 |
| Sauvegardes | 2 | 4 | 4 |
| Cohérence dev ↔ exécution | 2 | 5 | 2 |
| DuckDB `spatial` sur arm64 | 5 (figé dans l'image) | 4 (officiel, `INSTALL` à gérer) | 3 |
| GDAL / GeoPandas | 5 | 5 | 4 |
| Sécurité | 4 (isolé, mais port exposé au LAN) | 3 (non isolé, `127.0.0.1`) | 3 |
| Réversibilité | 5 | 4 | 4 |
| Coût de migration | 5 (nul) | 3 | 1 |
| **Total /70** | **49** | **58** | **39** |

---

## 5. Recommandation

**Passer à l'option B pour le Mac mini de Mathias**, en gardant A disponible en repli jusqu'à validation complète.

Arguments, par ordre d'importance :

1. **Un seul environnement.** Le Mac exécute déjà l'ETL et les tests en uv natif ; la CI et les sessions cloud aussi. Docker est le seul endroit où le code tourne différemment (Debian, autre Dockerfile, uv non figé dans l'image publiée). Le supprimer fait disparaître une catégorie entière de bugs (« ça marche sur le Mac mais pas dans l'image »), dont les trois déjà rencontrés en phase B (`pages/` absent, extension spatial absente, uv non figé).
2. **Aucune dépendance bloquante en natif.** Pas de GDAL à l'exécution, wheels arm64 disponibles, extension spatial officielle `osx_arm64` déjà présente sur la machine.
3. **Opérations quotidiennes plus simples** : base = un fichier visible dans le Finder ; sauvegarde = copie ; mise à jour = `git pull` + `uv sync` + redémarrage, enveloppés dans un script.
4. **Plus léger et plus rapide** sans machine virtuelle, pour un usage à une personne.

Ce que l'on perd : l'isolation du conteneur (acceptable pour un code personnel dont les dépendances sont figées) et une installation « clé en main » identique pour d'éventuels tiers — d'où la question 1.

---

## 6. Plan de migration (si B est validé)

Chaque étape est un commit distinct ; l'installation Docker continue de tourner jusqu'à l'étape 5.

| # | Étape | Fichiers | Vérification |
|---|---|---|---|
| 0 | ADR-0007 « Exécution native sur macOS » (révision partielle de la phase B) | `docs/adr/0007-*.md`, `docs/adr/README.md` | Relecture Mathias |
| 1 | Chemin de la base configurable via pydantic-settings (`MINISTERE_DB_PATH`, défaut = `data/ministere.duckdb` actuel → aucun changement pour Docker) ; fonction commune qui fait `LOAD spatial` et, en cas d'échec, `INSTALL` puis message clair si hors ligne | `viz/elections_queries.py`, `viz/economie_queries.py`, `viz/legislatif_queries.py`, `pages/1_📍_Géographie.py`, nouveau module de config, tests | `pytest`, CI verte sur le bon `headSha` |
| 2 | Scripts natifs : LaunchAgent (`RunAtLoad`, `KeepAlive` sur échec, `WorkingDirectory`, logs dans `~/Library/Logs/ministere-info/`, `--server.address 127.0.0.1 --server.runOnSave false`), script `ministere-ctl.sh start/stop/status/logs/update` | `deploy/native/*.plist`, `deploy/native/*.sh` | Lancement manuel |
| 3 | Sauvegarde réécrite : copie directe du fichier (app en lecture seule → copie cohérente), rotation 7 jours, destination configurable (idéalement disque externe ou dossier couvert par Time Machine) ; chemins du plist paramétrés | `scripts/backup_db.sh`, plist backup | Backup manuel + restauration testée |
| 4 | Essai en parallèle : natif sur le port **8502**, Docker inchangé sur 8501 ; comparer les 5 pages, la mémoire (Moniteur d'activité), le démarrage après redémarrage du Mac | — | **POINT D'ARRÊT : validation manuelle Mathias** |
| 5 | Bascule : `docker compose stop`, désactivation du LaunchAgent `com.ministere-info`, activation du LaunchAgent natif sur 8501. OrbStack reste installé 1 mois. | — | Redémarrage du Mac, app disponible seule |
| 6 | Documentation : `docs/deployment.md`, `deploy/README-deploy.md`, `CLAUDE.md` (modules + gotchas 12-13), `lessons-learned.md`. Décider du sort de `docker-publish.yml` (conserver en repli ou désactiver) | docs | Relecture |
| 7 | Optionnel : job CI `macos-14` (arm64) qui fait `uv sync --frozen` + `INSTALL spatial` + tests sans base, pour détecter tôt un problème propre au Mac | `.github/workflows/ci.yml` | Run CI |

Retour arrière à tout moment avant l'étape 6 : `launchctl bootout` du LaunchAgent natif puis `docker compose up -d`. La base n'est pas modifiée par la migration.

**Coordination** : les étapes 2, 3 et 6 touchent `deploy/` et `docs/deployment.md`, où un autre agent corrige actuellement les checksums et les Dockerfiles. À séquencer après la fusion de ses changements.

---

## 7. Risques

| Risque | Probabilité | Impact | Parade |
|---|---|---|---|
| Extension `spatial` absente après une mise à jour de DuckDB → pages Élections/Géographie/Économie en erreur | Moyenne | Fort | Étape 1 (INSTALL automatique) + `update` qui réinstalle ; `uv.lock` fige la version |
| ETL lancé pendant que l'app tourne → erreur de verrou DuckDB | Moyenne | Faible (erreur explicite en natif) | `ministere-ctl.sh stop` intégré aux commandes ETL documentées |
| L'app de tous les jours reflète les modifications de dev en cours | Élevée si même dossier | Moyen | Question 2 (copie séparée) |
| Mise à jour de macOS ou d'uv qui casse le lancement | Faible | Moyen | Python géré par uv (indépendant de macOS), version d'uv notée dans la doc ; repli Docker pendant 1 mois |
| Sauvegardes sur le même disque que la base | Actuel | Fort en cas de panne disque | Étape 3 : destination hors du disque ou Time Machine |
| Tiers ayant installé via `install.sh` laissés sans mise à jour | Inconnue | Moyen | Question 1 |
| Mesures de ce rapport (démarrage, mémoire) faites sur Linux cloud, sans base | Certaine | Faible | Mesures réelles à l'étape 4 |

---

## 8. Questions fermées pour Mathias

1. **D'autres personnes que toi utilisent-elles l'app installée via `install.sh` ?**
   - Oui → on garde l'image Docker et `install.sh` comme canal de distribution pour elles (B pour ton Mac seulement).
   - Non → B partout, l'image Docker est mise en sommeil après la période de repli.
2. **L'app « de tous les jours » doit-elle tourner :**
   - (a) directement depuis ton dossier de projet (le plus simple ; toute modification en cours est visible immédiatement), ou
   - (b) depuis une copie séparée (`~/Library/Application Support/ministere-info/`) mise à jour uniquement sur les versions publiées (tags) ?
3. **Valides-tu une période de double fonctionnement de deux semaines (natif sur 8502, Docker sur 8501) avant de désactiver le conteneur ?** Oui / Non.

---

## Sources

- [DuckDB — Installing Extensions](https://duckdb.org/docs/current/extensions/installing_extensions) (dossier `~/.duckdb/extensions/<version>/osx_arm64`, signature, installation hors ligne)
- [DuckDB — Concurrency](https://duckdb.org/docs/current/connect/concurrency) (un seul processus écrivain, lecteurs multiples en lecture seule)
- [DuckDB — Troubleshooting of Extensions](https://duckdb.org/docs/current/extensions/troubleshooting)
- [OrbStack — FAQ](https://docs.orbstack.dev/faq), [Efficiency](https://docs.orbstack.dev/efficiency), [Licensing](https://docs.orbstack.dev/licensing)
- [sliplane.io — OrbStack vs Docker Desktop (2026)](https://sliplane.io/blog/orbstack-vs-docker) (consommation au repos, source tierce)
- [launchd.plist(5)](https://keith.github.io/xcode-man-pages/launchd.plist.5.html) ; [Apple — Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
- [uv — Installing and managing Python](https://docs.astral.sh/uv/guides/install-python/)
- [stlite — README](https://github.com/whitphx/stlite) (limites Pyodide)
- [streamlit-desktop-app](https://github.com/ohtaman/streamlit-desktop-app) ; [Forum Streamlit — PyInstaller](https://discuss.streamlit.io/t/using-pyinstaller-or-similar-to-create-an-executable/902)
- [Streamlit Docs — Resource limits (Community Cloud)](https://docs.streamlit.io/knowledge-base/deploy/resource-limits)

Note : les sites duckdb.org et docs.orbstack.dev n'étaient pas accessibles directement depuis le conteneur cloud (proxy) ; leur contenu a été consulté via les extraits du moteur de recherche. Constats sur le dépôt vérifiés directement (fichiers, `uv.lock`, recherche d'imports) ; mesure de démarrage réalisée dans le conteneur cloud.
