# Infra — adapter l'installation native à la situation réelle du Mac (25/09/2026)

Date : 2026-09-25
Agent : ingenieur-infra
Périmètre : `deploy/native/*`, `scripts/backup_db.sh`, `deploy/tests/*`, `docs/deployment.md`
§3, `reports/a-faire-sur-le-mac.md` étape 5, ADR-0012 (addendum)

## Résumé exécutif

- Constat transmis par Mathias le 25/09 : **aucun conteneur/image Docker** sur le Mac
  (la période de double fonctionnement de l'ADR-0012 est sans objet) ; le projet est sur
  un **disque externe** (`/Volumes/le gros stockage/ministere-de-l-info`, chemin à
  espaces) ; un **ancien LaunchAgent de sauvegarde échoue** silencieusement.
- Robustesse aux espaces déjà largement acquise dans le code existant (guillemets
  systématiques, validation des métacaractères, marqueurs de plist) : ajout de cas de
  test avec le chemin réel plutôt que de correctifs de fond.
- Ajout : script intermédiaire `deploy/native/lancer-app.sh`, installé sur le disque
  interne, qui attend le montage du disque du projet (borné à 60 s) avant de démarrer
  Streamlit — évite l'échec instantané d'un `ProgramArguments` pointant vers un
  exécutable absent au démarrage de session.
- Ajout : `install-native.sh` détecte et désactive proprement (archive dans
  `desactives/`, ne supprime rien) l'ancien agent de sauvegarde en échec ; idempotent.
- Port par défaut passé à **8501 directement** (plus de transition 8502/8501).
- Documentation réécrite : `docs/deployment.md` §3 (8 étapes → 7, sans bascule),
  `reports/a-faire-sur-le-mac.md` étape 5 et en-tête (chemin réel, guillemets), ADR-0012
  complété par un addendum daté.
- Tests : `deploy/tests/test_native.sh` (125 assertions, 0 échec, +17 nouvelles),
  `deploy/tests/test_backup_db.sh` (49 assertions, 0 échec, +3 nouvelles),
  `deploy/tests/test_db_checksum.sh` inchangé (51 assertions, 0 échec). `bash -n` et
  `shellcheck` propres sur tous les scripts touchés.
- Décision non tranchée (recommandation ci-dessous, à trancher par Mathias) : garder le
  projet sur le disque externe, ou le déplacer en interne et réserver le disque externe
  aux sauvegardes.
- Rien poussé (branche de travail, worktree isolé).

## 1. Constat et diagnostic

### 1.1 Absence de Docker

`deploy/native/install-native.sh` et `docs/deployment.md` supposaient une période de
double fonctionnement (natif sur 8502, Docker sur 8501) issue de l'ADR-0012. Cette
hypothèse ne correspond à aucune réalité sur le Mac : ni conteneur, ni image, ni
`docker-compose` actif. Conséquence pratique : rien à comparer, rien à basculer.
`docs/deployment.md` §3 est réécrit en une procédure d'installation directe (voir §3
ci-dessous), et le port par défaut de `deploy/native/commun.sh` passe de `8502` à
`8501` (`PORT_PAR_DEFAUT`).

### 1.2 Disque externe et chemins à espaces

Chemin réel : `/Volumes/le gros stockage/ministere-de-l-info`. Audit des scripts
concernés :

- `deploy/native/commun.sh`, `install-native.sh`, `start.sh`, `stop.sh`, `status.sh`,
  `uninstall-native.sh` : toutes les expansions de variables de chemin étaient déjà
  entre guillemets doubles (vérifié par une recherche systématique des `$VAR` non
  protégés — aucun trouvé en dehors de chaînes déjà entre guillemets).
- `valider_chemin()` (commun.sh) refuse déjà `& < > | " \` et exige un chemin absolu,
  mais n'interdisait pas les espaces (aucune raison de le faire : ni le XML du plist, ni
  `sed` avec délimiteur `|`, ni `cp`/`cd` correctement quotés n'en souffrent).
- `rendre_modele()` : substitution par marqueurs `@...@` dans un fichier XML (pas
  d'interprétation shell du chemin), avec validation finale `plutil -lint` — un chemin à
  espaces devient un contenu XML texte comme un autre.
- `scripts/backup_db.sh` : toutes les variables de chemin déjà entre guillemets ;
  `destination_disponible()` utilise `cut -d/ -f1-3` (découpe sur `/`, insensible aux
  espaces) pour vérifier qu'un point de montage `/Volumes/...` existe avant d'y créer un
  dossier.
- Point vérifié spécifiquement : `df -P "$DB_PATH" | awk 'NR==2{print $1}'` (détection
  « même disque que la base ») lit le champ 1 (périphérique, ex. `/dev/disk4s1`), pas le
  point de montage — un point de montage à espaces (`Mounted on` en fin de ligne) ne
  décale pas ce champ. Pas de bug trouvé sur ce point.

Conclusion : le code était déjà robuste aux chemins à espaces (héritage probable d'un
audit antérieur). Le travail a consisté à **documenter** ce constat et à **ajouter des
tests explicites** avec le chemin réel plutôt qu'à corriger des bugs :

- `deploy/tests/test_native.sh` scénario N20 : projet installé sous
  `.../Volumes/le gros stockage/ministere-de-l-info`, sauvegarde vers un sous-dossier du
  même disque.
- `deploy/tests/test_backup_db.sh` scénario B13 : même schéma côté `backup_db.sh`,
  vérifie en plus l'avertissement « même disque » quand source et destination
  partagent le même volume.
- Les scénarios pré-existants N5 (`install-native.sh`) et B11 (`backup_db.sh`)
  couvraient déjà des chemins à espaces génériques ; les nouveaux scénarios collent au
  cas réel (nom de disque, structure `/Volumes/...`) pour la traçabilité.

### 1.3 Ancien agent de sauvegarde en échec

`com.crocdeine.ministere-info.backup` existe déjà sous ce nom (l'ADR-0012 prévoyait de
remplacer un ancien agent au même identifiant). Jusqu'ici, `install-native.sh`
l'écrasait silencieusement (`decharger_agent` + `rendre_modele` sur le même fichier).
Ajout d'une étape de détection explicite, tracée dans le journal et archivée :

- Nouvelle fonction `retirer_ancienne_sauvegarde()` (`deploy/native/commun.sh`) : lit le
  plist existant, extrait le chemin du script `backup_db.sh` référencé
  (`ProgramArguments`), et s'il n'existe plus sur disque (projet déplacé), décharge
  l'agent et déplace le plist dans `~/Library/LaunchAgents/desactives/` avec un suffixe
  horodaté (jamais de suppression). Idempotente : ne se déclenche pas si le script
  référencé existe (y compris après un premier passage, puisque le nouveau plist pointe
  vers le script du projet courant).
- Appelée dans `install-native.sh`, étape 8, avant l'installation du nouvel agent.
- Testée : `deploy/tests/test_native.sh` scénario N22 (détection, archivage, plist de
  remplacement valide, idempotence sur relance).

## 2. Attente du montage du disque au démarrage

### 2.1 Problème

Le `ProgramArguments` du LaunchAgent applicatif appelait directement
`<projet>/.venv/bin/python -m streamlit run app.py ...`. Si ce chemin est sur un disque
externe non encore monté à l'ouverture de session, `launchd` échoue à trouver
l'exécutable : échec instantané, retenté au rythme de `ThrottleInterval` (10 s
auparavant) — proche d'une boucle de crash rapide tant que le disque n'est pas monté.

### 2.2 Solution retenue

Un script intermédiaire, `deploy/native/lancer-app.sh`, est généré par
`install-native.sh` et installé sur le **disque interne**
(`~/.config/ministere-info/lancer-app.sh`, jamais dans le dossier du projet). C'est ce
script que `ProgramArguments` invoque désormais (`/bin/bash <lanceur>`). Il :

1. Attend, par pas de 2 s (configurable via `MINISTERE_LANCER_INTERVALLE` — utilisé
   uniquement par les tests), jusqu'à 60 s (`MINISTERE_LANCER_ATTENTE_MAX`) que le
   Python du `.venv` et `app.py` du projet redeviennent accessibles.
2. Journalise un message explicite dès le premier échec de vérification (« pas encore
   monté ? »), puis un message d'erreur explicite en cas d'abandon après le délai.
3. Une fois le projet disponible, `cd` dans le projet et `exec` Streamlit (mêmes
   arguments qu'avant : écoute `127.0.0.1`, port configuré).

`ThrottleInterval` du plist applicatif est porté de 10 s à 15 s : le lanceur consomme
déjà jusqu'à 60 s avant d'échouer en cas de disque absent, ce qui borne naturellement le
rythme de relance dans ce cas ; les 15 s couvrent les autres échecs plus rapides
(script absent, erreur immédiate de Streamlit).

**Limite documentée** (`docs/deployment.md` §1 et §2.6, ADR-0012 addendum) : si le
disque reste débranché plus de 60 secondes, l'application reste indisponible jusqu'au
cycle de relance suivant de launchd, ou jusqu'à `./deploy/native/start.sh` une fois le
disque rebranché. Pas de garantie de disponibilité disque débranché — situation
normale et attendue pour une application « personnelle » sur disque externe.

### 2.3 Modifications techniques

- `deploy/native/lancer-app.sh` (nouveau, modèle avec marqueurs `@PROJECT_DIR@`,
  `@PYTHON@`, `@PORT@`).
- `deploy/native/commun.sh` : constante `LANCEUR_APP`, fonction `rendre_script()`
  (rendu de script shell : substitution, `chmod +x`, pas de `plutil`), marqueur
  `@LANCEUR@` ajouté à `rendre_modele()`.
- `deploy/native/ministere-info.plist` : `ProgramArguments` remplacé par
  `["/bin/bash", "@LANCEUR@"]` ; `ThrottleInterval` 10 → 15.
- `deploy/native/install-native.sh` : génère `lancer-app.sh` avant le plist applicatif.
- Tests : `deploy/tests/test_native.sh` scénarios N1 (assertions mises à jour pour le
  nouveau `ProgramArguments`) et N21 (exécution directe de `lancer-app.sh` avec un
  délai réduit, vérifie le code de sortie non nul et les deux messages journalisés).

## 3. Documentation

- `docs/deployment.md` : en-tête (tableau des deux modes, variable `PROJET` avec
  guillemets systématiques), §1 (limite disque externe documentée, nouvelle ligne dans
  le tableau des emplacements pour `lancer-app.sh` et `desactives/`), §2 (port par
  défaut 8501, retrait des mentions de transition), §2.6 (nouvelle ligne de dépannage),
  **§3 entièrement réécrit** (7 étapes d'installation directe, POINT D'ARRÊT conservé
  avant la désactivation de l'ancien agent de sauvegarde, retour arrière simplifié),
  §4 (Docker requalifié en repli non déployé, références à l'ancienne bascule
  corrigées).
- `reports/a-faire-sur-le-mac.md` : en-tête daté et chemin du projet mis à jour avec
  guillemets ; étape 0 (chemin) et étape 2 (arrêt/redémarrage de l'application — plus de
  `docker stop`/`docker start`, remplacés par `deploy/native/stop.sh`/`start.sh`
  conditionnels) ; étape 5 réécrite (installation directe sur 8501, mention explicite
  de la désactivation de l'ancien agent de sauvegarde, POINT D'ARRÊT conservé).
- `docs/adr/0012-execution-native-mac.md` : addendum daté 2026-09-25 (constats, quatre
  compléments d'exécution, question ouverte pour Mathias reprise ci-dessous). L'ADR
  n'est pas révisé sur le fond : la décision du 24/09 reste valide.

## 4. Procédure de test manuel (Mac, à faire par Mathias ou Claude Code local)

1. `cd "/Volumes/le gros stockage/ministere-de-l-info" && git pull` (branche à fusionner
   d'abord).
2. `docker ps` → confirmer l'absence de conteneur `ministere-info` (déjà su, à
   revérifier).
3. Copie de sécurité : `cp -p data/ministere.duckdb ~/ministere-avant-installation-native.duckdb`.
4. `./deploy/native/install-native.sh` → suivre les 9 étapes affichées. **Vérifier le
   message concernant l'ancien agent de sauvegarde** (`Ancien agent de sauvegarde
   détecté ... désactivé` s'il y en a un, ou rien si l'agent actuel est déjà valide) et
   le contenu de `~/Library/LaunchAgents/desactives/` avant de continuer (POINT
   D'ARRÊT — ne rien supprimer sans validation).
5. `./deploy/native/status.sh` → `Santé : OK (répond)`, adresse `http://localhost:8501`.
6. `./deploy/native/install-native.sh --sauvegarde-vers <dossier hors du disque du
   projet si possible>` puis `./scripts/backup_db.sh` → ligne `OK : ministere-...duckdb`.
7. **Test réel de la limite disque externe** (à faire une fois, en connaissance de
   cause) : débrancher le disque, redémarrer le Mac, patienter plus d'une minute après
   l'ouverture de session, rebrancher le disque, puis
   `tail -n 20 ~/Library/Logs/ministere-info/app.err.log` — doit contenir un message
   « indisponible après 60s », puis `./deploy/native/start.sh` doit faire répondre
   l'application.
8. Redémarrage de contrôle standard (disque branché) : `./deploy/native/status.sh` doit
   indiquer `OK` sans rien relancer à la main.

## 5. Risques et limites

- **Disque externe débranché** : indisponibilité de l'application au-delà de 60 s après
  l'ouverture de session (accepté, documenté). Un débranchement en cours d'usage (pas au
  démarrage) n'est pas couvert par `lancer-app.sh` (il ne s'exécute qu'au lancement) —
  l'application plantera probablement (I/O error DuckDB/Streamlit) et sera relancée par
  `KeepAlive`, retombant dans le même scénario d'attente.
- **Un seul disque de sauvegarde partagé avec le disque du projet** : si aucun autre
  disque n'est disponible dans l'immédiat, `backup_db.sh` continuera de fonctionner
  (avertissement journalisé) mais une panne du disque externe emporterait base et
  sauvegardes. Voir recommandation §6.
- **Détection de l'ancien agent** : ne couvre que le label connu
  (`com.crocdeine.ministere-info.backup`, historiquement le même que la nouvelle
  version). Si un agent d'un label totalement différent existe par ailleurs (non
  identifié dans les constats transmis), il ne sera pas détecté automatiquement ; à
  vérifier manuellement avec `launchctl list | grep -i ministere`.

## 6. Recommandation — emplacement du projet (à trancher par Mathias)

**Recommandation : déplacer le projet sur le disque interne** (ex.
`~/Developer/ministere-de-l-info`) et réserver le disque externe aux **sauvegardes**.

Arguments :

- Élimine la limite du §2 (attente de montage au démarrage) : plus de dépendance à un
  disque externe pour que l'application démarre.
- Un disque externe dédié aux sauvegardes répond directement au besoin déjà identifié
  dans l'ADR-0012 (« destination hors du disque interne ») sans readonner l'application
  elle-même vulnérable à un débranchement.
- Le disque interne d'un Mac mini M4 est un SSD rapide et fiable ; le disque externe,
  généralement plus lent et davantage manipulé (débranchements), est un meilleur candidat
  pour une destination secondaire que pour l'hébergement primaire.
- Réduit la surface de risque : une panne du disque externe n'affecte plus que les
  sauvegardes (récupérables autrement, ex. régénération partielle par ETL), pas
  l'application elle-même ni sa base de travail.

Argument en sens inverse (garder sur le disque externe) : évite une migration
(temps, risque de manipulation), et le disque externe a peut-être été choisi
initialement pour une raison d'espace disque sur l'interne — à vérifier auprès de
Mathias avant toute migration.

**Procédure de déplacement, si retenue** (à exécuter sur le Mac, jamais depuis le cloud) :

```bash
./deploy/native/stop.sh
mkdir -p ~/Developer
cp -a "/Volumes/le gros stockage/ministere-de-l-info" ~/Developer/ministere-de-l-info
cd ~/Developer/ministere-de-l-info
uv sync --frozen --group etl
./deploy/native/install-native.sh --projet ~/Developer/ministere-de-l-info \
  --sauvegarde-vers "/Volumes/le gros stockage/ministere-info-sauvegardes"
```

Vérifier `./deploy/native/status.sh` (santé OK sur le nouveau chemin), comparer la
taille de la base copiée, puis seulement après validation, retirer l'ancienne
installation (`git status` propre sur l'ancien dossier avant suppression — ne pas
supprimer avant confirmation explicite de Mathias, conformément à la règle générale de
prudence sur les suppressions).

## 7. Vérifications effectuées (session cloud)

- `bash -n` sur tous les scripts `deploy/native/*.sh`, `scripts/backup_db.sh`,
  `deploy/tests/*.sh` : aucune erreur de syntaxe.
- `uvx --from shellcheck-py shellcheck` sur les mêmes fichiers : aucun avertissement.
- `bash deploy/tests/test_native.sh` : 125 assertions, 0 échec.
- `bash deploy/tests/test_backup_db.sh` : 49 assertions, 0 échec.
- `bash deploy/tests/test_db_checksum.sh` (non modifié, contrôle de non-régression) :
  51 assertions, 0 échec.
- Pas de `docker compose config` (pas de modification des fichiers Docker dans cette
  tâche — hors périmètre).

## 8. Fichiers modifiés ou créés

- `deploy/native/lancer-app.sh` (nouveau)
- `deploy/native/commun.sh`
- `deploy/native/install-native.sh`
- `deploy/native/ministere-info.plist`
- `deploy/tests/test_native.sh`
- `deploy/tests/test_backup_db.sh`
- `docs/deployment.md`
- `reports/a-faire-sur-le-mac.md`
- `docs/adr/0012-execution-native-mac.md`
- `reports/infra-native-mac-situation-reelle-2026-09-25.md` (ce rapport)
- `reports/README.md` (index)
