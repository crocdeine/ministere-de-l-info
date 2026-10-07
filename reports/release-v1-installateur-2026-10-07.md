# Version 1.0 — installateur en une commande (2026-10-07)

## Résumé exécutif

- `install.sh` et `uninstall.sh` à la racine ; commande : `curl -fsSL …/v1.0.0/install.sh | bash`.
- Installation dans `~/Library/Application Support/Ministere-de-l-Info/`, icône locale
  `~/Applications/Ministère de l'Info.app`, journaux `~/Library/Logs/Ministere-de-l-Info/`.
- Sans sudo ni jeton ; uv 0.11.16 et Python 3.12 installés dans le dossier d'installation.
- Base : release `DB_TAG` (actuellement `db-2026-10-04`), SHA-256 vérifié, reprise, conservée si inchangée.
- Scénario local vert : installation 87 s (131 s au premier essai), 1,6 Go installés, lancement 2 s,
  HTTP 200, mise à jour 5 s (base conservée), désinstallation complète, aucun processus résiduel.
- Testés en plus : port 8501 occupé → 8502 ; empreinte fausse → échec, base existante intacte ;
  reprise de téléchargement (fonction `telecharger`, serveur HTTP local).
- shellcheck propre, ruff propre, pytest 303 réussis (base absente du worktree : 363 ignorés).
- Version 1.0.0 (`pyproject.toml`, `uv.lock` : seule la ligne de version), `CHANGELOG.md`,
  `docs/release-notes-v1.0.md` (brouillon).
- Rien n'a été poussé ni publié. Reste : base de la vague B (`DB_TAG`), tag `v1.0.0`, test réel.

## Changements

| Fichier | Contenu |
|---|---|
| `install.sh` | 7 étapes : contrôles (macOS, espace 3 Go / 1 Go), uv épinglé, archive du tag, `uv sync --frozen --no-dev --python 3.12`, extension `spatial`, base, icône |
| `uninstall.sh` | Confirmation lue sur `/dev/tty` (compatible `curl | bash`), `--oui`, arrêt du serveur, suppression des trois emplacements |
| `pyproject.toml`, `uv.lock` | 1.0.0, description |
| `CHANGELOG.md`, `docs/release-notes-v1.0.md` | Nouveaux ; commentaires « Directeur : » à compléter (vague B) |
| `README.md`, `docs/deployment.md` (§0), `docs/guide-utilisateur.md`, `docs/reprise.md` | Installation, mise à jour, désinstallation ; cible de production du 2026-10-07 |

Choix techniques (sans engagement de fond) :
- Tout est dans `main`, appelée en dernière ligne ; commandes lancées avec `</dev/null`.
- uv, Python (`UV_PYTHON_INSTALL_DIR`), cache (vidé après installation) et venv
  (`UV_PROJECT_ENVIRONMENT`) restent dans le dossier d'installation : la désinstallation n'oublie rien,
  sauf `~/.duckdb` (extension `spatial`, partagée, volontairement conservée).
- Le lanceur de l'icône réutilise `deploy/native/commun.sh` (`app_repond`, `attendre_app`,
  `port_occupe_par`) ; serveur en arrière-plan, `--server.fileWatcherType none`, PID et port mémorisés.
- Mise à jour : le serveur lancé par l'icône est arrêté avant le remplacement du code.
- `uv.lock` : `uv lock` (0.11.16) réécrivait 2 000 lignes (format) ; seule la ligne de version a été
  modifiée, `uv lock --check` passe avec uv 0.11.16 et 0.12.17.

## Procédure de test manuel (Mathias)

Test local (déjà passé par l'agent, à refaire si besoin) :

```bash
T="/Volumes/le gros stockage/outils/tmp/test-install"
export MI_SOURCE_ARCHIVE="$T/src/code.tar.gz" MI_DB_ARCHIVE="$T/src/ministere.duckdb.gz" MI_INSTALL_DIR="$T/Application Support/Ministere-de-l-Info" MI_APPS_DIR="$T/Applications" MI_LOG_DIR="$T/Logs"
bash install.sh
MI_NO_BROWSER=1 "$T/Applications/Ministère de l'Info.app/Contents/MacOS/lancer"
bash uninstall.sh --oui
```

(`$T/src` contient l'archive `git archive --prefix=ministere-de-l-info-1.0.0/` et la base compressée
avec son `.sha256` ; à régénérer après tout nouveau commit.)

Test réel, après publication (sur un compte utilisateur macOS de test de préférence) :
1. Coller la commande du README ; noter la durée.
2. Finder > Aller > Départ > Applications : double-clic sur l'icône → la page s'ouvre.
3. Fermer l'onglet, rouvrir l'icône → même page, immédiatement.
4. Relancer la commande → « Base déjà à jour, conservée ».
5. Couper le Wi-Fi pendant le téléchargement de la base, relancer → reprise.
6. Désinstaller avec la commande `uninstall.sh`, répondre `o` ; vérifier que les trois emplacements
   ont disparu.

## Liste de publication (directeur, après accord de Mathias)

1. Fusionner la vague B ; publier la base v1.0 (`scripts/publish_db.sh`, tag `db-AAAA-MM-JJ`,
   assets `ministere.duckdb.gz` et `ministere.duckdb.gz.sha256` = empreinte de l'archive).
2. Mettre `DB_TAG` à jour dans `install.sh` ; compléter les commentaires « Directeur : » de
   `CHANGELOG.md` et `docs/release-notes-v1.0.md` ; date de la 1.0.0 dans le CHANGELOG.
3. Refaire le scénario local sur le commit final ; fusionner `release/v1.0` dans `main` (PR squash),
   CI verte sur le `headSha` du commit fusionné.
4. Tag `v1.0.0` sur ce commit, pousser le tag (la commande lit `install.sh` à ce tag et télécharge
   `archive/refs/tags/v1.0.0.tar.gz`). Release GitHub `v1.0.0` avec les notes de version ; aucun
   asset obligatoire (le code vient de l'archive du tag).
5. Test réel (§ ci-dessus) avant de diffuser la commande.

## Risques et limites

| Risque | Parade / état |
|---|---|
| Le tag `v1.0.0` ne doit plus bouger : la commande `v1.0.0` réinstalle toujours la 1.0.0 | Nouvelle version = nouveau tag et nouvelle commande à communiquer |
| `DB_TAG` oublié | Étape 2 de la liste ; la base actuelle `db-2026-10-04` ne contient pas J2/AMO |
| Mac Intel | Non testé (dit dans la doc) |
| Serveur tournant jusqu'à la fermeture de session (≈ 300-500 Mo de mémoire) | Accepté ; pas d'arrêt automatique |
| Autre application Streamlit sur le port mémorisé | Le lanceur vérifie aussi que le PID mémorisé est vivant |
| Icône générique | Pas de logo `.icns` dans le dépôt ; à ajouter si souhaité |
| Reprise du téléchargement non testée contre GitHub | Testée contre un serveur local ; à vérifier au test réel (étape 5) |
